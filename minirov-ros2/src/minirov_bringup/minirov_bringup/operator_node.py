#!/usr/bin/env python3
"""
operator_node.py
================
Supervised autonomy operator interface for miniROV.

Subscribes:
  /minirov/llm_response   (minirov_msgs/LLMResponse)   — proposed commands from LLM
  /minirov/observations   (minirov_msgs/LLMObservation) — proactive warnings from LLM

Publishes:
  /minirov/user_input     (std_msgs/String)             — free-text operator input
  /minirov/commands       (minirov_msgs/VehicleCommand) — confirmed commands to mavlink_node

Closes the supervised autonomy loop:
  LLM proposes → operator reviews → operator confirms (y) or rejects (n) → command sent

LLMResponse → VehicleCommand conversion:
  Shared fields are copied directly; a ROS timestamp is added on confirmation.
  Fields: action, speed, direction, duration_sec, reasoning, safety_note
"""

import cmd
import threading
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from std_msgs.msg import String
from minirov_msgs.msg import LLMResponse, LLMObservation, VehicleCommand


# ── ANSI colour helpers ────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    DIM     = "\033[2m"


def banner(text: str, colour: str = C.CYAN) -> str:
    line = "─" * 60
    return f"\n{colour}{C.BOLD}{line}\n  {text}\n{line}{C.RESET}"


# ── Node ───────────────────────────────────────────────────────────────────

class OperatorNode(Node):
    """
    Terminal-based operator interface.

    Input is handled in a dedicated daemon thread so the ROS 2 spin loop
    (subscriptions, timers) is never blocked waiting for the operator.
    """

    def __init__(self):
        super().__init__("operator_node")

        # ── Subscriptions ──────────────────────────────────────────────────
        self.create_subscription(
            LLMResponse,
            "/minirov/llm_response",
            self._on_llm_response,
            10,
        )
        self.create_subscription(
            LLMObservation,
            "/minirov/observations",
            self._on_observation,
            10,
        )

        # ── Publishers ─────────────────────────────────────────────────────
        self._user_input_pub = self.create_publisher(String, "/minirov/user_input", 10)
        self._commands_pub   = self.create_publisher(VehicleCommand, "/minirov/commands", 10)

        # ── State ──────────────────────────────────────────────────────────
        self._pending: LLMResponse | None = None
        self._pending_lock = threading.Lock()

        # ── Input thread ───────────────────────────────────────────────────
        input_thread = threading.Thread(
            target=self._input_loop, daemon=True, name="operator_input"
        )
        input_thread.start()

        # ── Startup banner ─────────────────────────────────────────────────
        print(banner("miniROV Operator Console  —  operator_node"))
        print(f"{C.DIM}  SUB  /minirov/llm_response{C.RESET}")
        print(f"{C.DIM}  SUB  /minirov/observations{C.RESET}")
        print(f"{C.DIM}  PUB  /minirov/user_input{C.RESET}")
        print(f"{C.DIM}  PUB  /minirov/commands{C.RESET}")
        print(f"\n{C.DIM}  y/yes → confirm    n/no → reject    status → show pending{C.RESET}")
        print(f"{C.DIM}  Any other input    → publish to /minirov/user_input{C.RESET}")
        print(f"{C.DIM}  q/quit or Ctrl-C   → shutdown{C.RESET}\n")
        self.get_logger().info("operator_node started")

    # ── Subscription callbacks ─────────────────────────────────────────────

    def _on_llm_response(self, msg: LLMResponse) -> None:
        """Store the proposed command and prompt for confirmation."""
        with self._pending_lock:
            self._pending = msg

        print(banner("⚡  LLM Proposed Command", C.MAGENTA))
        print(f"  {C.BOLD}Action    :{C.RESET} {msg.action}")
        print(f"  {C.BOLD}Direction :{C.RESET} {msg.direction}")
        print(f"  {C.BOLD}Speed     :{C.RESET} {msg.speed}")
        print(f"  {C.BOLD}Duration  :{C.RESET} {msg.duration_sec} s")

        if msg.reasoning:
            print(f"  {C.DIM}Reasoning  : {msg.reasoning}{C.RESET}")
        if msg.safety_note:
            print(f"  {C.YELLOW}Safety note: {msg.safety_note}{C.RESET}")

        print(f"\n{C.YELLOW}{C.BOLD}  Confirm? [y/n] >{C.RESET} ", end="", flush=True)

    def _on_observation(self, msg: LLMObservation) -> None:
        colour = C.RED if msg.severity == "CRITICAL" else C.YELLOW if msg.severity == "WARNING" else C.CYAN
        print(f"\n{colour}{C.BOLD}[{msg.severity}]{C.RESET} {msg.observation}")
        if msg.recommended_action:
            print(f"  {C.DIM}→ {msg.recommended_action}{C.RESET}")
        print(f"{C.DIM}> {C.RESET}", end="", flush=True)

    # ── Input loop ─────────────────────────────────────────────────────────

    def _input_loop(self) -> None:
        """Blocking input loop in its own thread — never starves the spin loop."""
        while rclpy.ok():
            try:
                raw = input(f"{C.DIM}> {C.RESET}").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                self._shutdown()
                break

            if not raw:
                continue

            lower = raw.lower()

            if lower in ("q", "quit", "exit"):
                self._shutdown()
                break
            elif lower == "status":
                self._print_status()
            elif lower in ("y", "yes"):
                self._confirm_command()
            elif lower in ("n", "no"):
                self._reject_command()
            else:
                self._publish_user_input(raw)

    # ── Confirmation / rejection ───────────────────────────────────────────

    def _confirm_command(self) -> None:
        """
        Copy shared fields from LLMResponse → VehicleCommand, stamp, and publish.

        LLMResponse and VehicleCommand share:
            action, speed, direction, duration_sec, reasoning, safety_note
        The only addition is the ROS timestamp so mavlink_node knows when the
        operator approved the command.
        """
        with self._pending_lock:
            pending = self._pending
            self._pending = None

        if pending is None:
            print(f"  {C.DIM}Nothing to confirm.{C.RESET}")
            return

        cmd = VehicleCommand()

        # Direct field copy — schemas are intentionally identical
        cmd.action       = pending.action
        cmd.speed        = pending.speed
        cmd.direction    = pending.direction
        cmd.duration_sec = pending.duration_sec
        cmd.reasoning    = pending.reasoning
        cmd.safety_note  = pending.safety_note

        # Stamp with current ROS time (operator approval moment)
        cmd.stamp = self.get_clock().now().to_msg()
        self._commands_pub.publish(cmd)

        print(f"\n{C.GREEN}{C.BOLD}  ✓ Confirmed → /minirov/commands{C.RESET}")
        print(f"  {C.DIM}action={cmd.action}  direction={cmd.direction}  "
              f"speed={cmd.speed}  duration={cmd.duration_sec}s{C.RESET}\n")
        self.get_logger().info(
            f"Command confirmed: action={cmd.action} direction={cmd.direction} "
            f"speed={cmd.speed} duration={cmd.duration_sec}s"
        )

    def _reject_command(self) -> None:
        with self._pending_lock:
            pending = self._pending
            self._pending = None

        if pending is None:
            print(f"  {C.DIM}Nothing to reject.{C.RESET}")
            return

        print(f"\n{C.RED}{C.BOLD}  ✗ Rejected.{C.RESET}")
        print(f"  {C.DIM}action={pending.action}{C.RESET}\n")
        self.get_logger().info(f"Command rejected: action={pending.action}")

    # ── User input ─────────────────────────────────────────────────────────

    def _publish_user_input(self, text: str) -> None:
        msg = String()
        msg.data = text
        self._user_input_pub.publish(msg)
        print(f"  {C.DIM}→ /minirov/user_input{C.RESET}")
        self.get_logger().debug(f"user_input: {text}")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _print_status(self) -> None:
        with self._pending_lock:
            p = self._pending
        if p is None:
            print(f"  {C.DIM}No pending command.{C.RESET}")
        else:
            print(f"  {C.YELLOW}Pending: action={p.action}  direction={p.direction}  "
                  f"speed={p.speed}  duration={p.duration_sec}s{C.RESET}")

    def _shutdown(self) -> None:
        print(f"\n{C.DIM}Shutting down operator_node…{C.RESET}")
        self.get_logger().info("operator_node shutting down")
        self.destroy_node()
        rclpy.shutdown()


# ── Entry point ────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = OperatorNode()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()