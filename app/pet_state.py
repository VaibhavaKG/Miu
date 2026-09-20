"""
Pet State Machine and Personality Engine for Miu Desktop Companion.

Implements natural, active, desktop-aware behaviors:
States: IDLE, WALKING, RUNNING, SITTING, SLEEPING, STRETCHING, CURIOUS, HAPPY, FOCUSED, BREAK, CLIMBING, EXPLORING
Personalities: CALM, PLAYFUL, SLEEPY, ENERGETIC, FOCUSED
"""

import math
import random
import time
from enum import Enum


class PetState(Enum):
    IDLE = "IDLE"
    WALKING = "WALKING"
    RUNNING = "RUNNING"
    SITTING = "SITTING"
    SLEEPING = "SLEEPING"
    STRETCHING = "STRETCHING"
    CURIOUS = "CURIOUS"
    HAPPY = "HAPPY"
    FOCUSED = "FOCUSED"
    BREAK = "BREAK"
    CLIMBING = "CLIMBING"
    EXPLORING = "EXPLORING"
    INVESTIGATING = "INVESTIGATING"
    PLAYING = "PLAYING"
    WATCHING = "WATCHING"
    PLAYING_YARN = "PLAYING_YARN"


class Personality:
    """Configures behavioral parameters that distinctly alter pet movement, activity, and habits."""
    PROFILES = {
        "calm": {
            "name": "Calm",
            "speed_mult": 0.75,
            "idle_min_sec": 2.5,
            "idle_max_sec": 5.5,
            "chase_threshold_px": 80,
            "sit_weight": 45,
            "sleep_weight": 8,       # Brief occasional nap only
            "sleep_duration_sec": 9.0,
            "stretch_weight": 22,
            "roam_weight": 45,
            "climb_chance": 0.12,
            "sprint_chance": 0.0,
        },
        "playful": {
            "name": "Playful",
            "speed_mult": 1.25,
            "idle_min_sec": 1.0,
            "idle_max_sec": 3.0,
            "chase_threshold_px": 45,
            "sit_weight": 15,
            "sleep_weight": 4,
            "sleep_duration_sec": 5.0,  # Short quick naps
            "stretch_weight": 20,
            "roam_weight": 70,
            "climb_chance": 0.28,
            "sprint_chance": 0.35,
        },
        "sleepy": {
            "name": "Sleepy",
            "speed_mult": 0.65,
            "idle_min_sec": 3.0,
            "idle_max_sec": 7.0,
            "chase_threshold_px": 110,
            "sit_weight": 35,
            "sleep_weight": 18,      # More frequent naps
            "sleep_duration_sec": 9.0,
            "stretch_weight": 25,
            "roam_weight": 35,
            "climb_chance": 0.08,
            "sprint_chance": 0.0,
        },
        "energetic": {
            "name": "Energetic",
            "speed_mult": 1.35,
            "idle_min_sec": 0.8,
            "idle_max_sec": 2.5,
            "chase_threshold_px": 35,
            "sit_weight": 10,
            "sleep_weight": 2,       # Rarely sleeps
            "sleep_duration_sec": 8.5,
            "stretch_weight": 18,
            "roam_weight": 80,
            "climb_chance": 0.32,
            "sprint_chance": 0.45,
        },
        "focused": {
            "name": "Focused",
            "speed_mult": 0.70,
            "idle_min_sec": 5.0,
            "idle_max_sec": 12.0,
            "chase_threshold_px": 140,
            "sit_weight": 55,
            "sleep_weight": 5,
            "sleep_duration_sec": 6.0,  # Short deliberate rest
            "stretch_weight": 15,
            "roam_weight": 30,
            "climb_chance": 0.10,
            "sprint_chance": 0.0,
        },
    }

    @classmethod
    def get(cls, personality_key):
        return cls.PROFILES.get(str(personality_key).lower(), cls.PROFILES["calm"])


class PetStateMachine:
    def __init__(self, personality_key="calm"):
        self.personality_key = personality_key
        self.profile = Personality.get(personality_key)
        self.state = PetState.IDLE
        self.state_timer = 0.0
        self.sub_frame = 0
        self.is_paused = False
        self.is_dragged = False
        self.curious_timer = 0.0
        self.happy_timer = 0.0
        self.focus_mode = False
        self.break_mode = False

        # Climbing mission tracking
        self.current_mission = None
        self.mission_step = 0
        self.climbing_subaction = "none"

        # Autonomous roaming timers (short, natural breathers)
        self.next_idle_action_time = time.time() + random.uniform(1.5, 4.0)

    def set_personality(self, personality_key):
        self.personality_key = personality_key
        self.profile = Personality.get(personality_key)

    def set_focus_mode(self, active):
        self.focus_mode = active
        if active:
            self.break_mode = False
            self.state = PetState.FOCUSED
            self.state_timer = 0.0
            self.next_idle_action_time = time.time() + random.uniform(6.0, 12.0)
        elif self.state == PetState.FOCUSED:
            self.state = PetState.IDLE
            self.next_idle_action_time = time.time() + random.uniform(1.5, 3.5)

    def set_break_mode(self, active):
        self.break_mode = active
        if active:
            self.focus_mode = False
            self.state = PetState.BREAK
            self.state_timer = 0.0
            self.next_idle_action_time = time.time() + random.uniform(1.0, 2.5)
        elif self.state == PetState.BREAK:
            self.state = PetState.IDLE
            self.next_idle_action_time = time.time() + random.uniform(1.5, 3.5)

    def pet_interaction(self):
        """Called when user clicks / pets the companion."""
        self.state = PetState.HAPPY
        self.happy_timer = 2.5
        self.state_timer = 0.0

    def get_effective_speed(self, base_speed=10.0, speed_setting="normal"):
        speed_modifiers = {
            "slow": 0.7,
            "normal": 1.0,
            "fast": 1.4,
        }
        mult = self.profile["speed_mult"] * speed_modifiers.get(speed_setting, 1.0)
        if self.state == PetState.RUNNING:
            mult *= 1.55
        elif self.state == PetState.CLIMBING:
            mult *= 0.75  # Deliberate climbing pace
        elif self.state in (PetState.FOCUSED, PetState.SLEEPING):
            mult *= 0.65
        return base_speed * mult

    def should_pick_new_destination(self):
        """Returns True if Miu is idle/sitting/sleeping and ready to roam again."""
        if self.is_paused or self.is_dragged or self.happy_timer > 0:
            return False
        if self.state in (PetState.WALKING, PetState.RUNNING, PetState.CLIMBING):
            return False
        return time.time() >= self.next_idle_action_time

    def on_reached_destination(self, post_action="idle"):
        """Called by movement controller when Miu arrives at a waypoint."""
        self.state_timer = 0.0

        if self.focus_mode:
            self.state = PetState.FOCUSED
            # Sits calmly for 6-14s before next quiet stroll
            self.next_idle_action_time = time.time() + random.uniform(7.0, 14.0)
            return

        if self.break_mode:
            # Short energetic pauses (1-2.5s)
            self.state = PetState.BREAK
            self.next_idle_action_time = time.time() + random.uniform(1.0, 2.5)
            return

        # Normal roaming post-action
        if post_action == "sit":
            self.state = PetState.SITTING
            self.next_idle_action_time = time.time() + random.uniform(
                self.profile["idle_min_sec"] * 1.2, self.profile["idle_max_sec"]
            )
        elif post_action == "look":
            self.state = PetState.CURIOUS
            self.next_idle_action_time = time.time() + random.uniform(1.5, 3.0)
        elif post_action == "stretch":
            self.state = PetState.STRETCHING
            self.next_idle_action_time = time.time() + random.uniform(1.8, 3.2)
        else:
            self.state = PetState.IDLE
            self.next_idle_action_time = time.time() + random.uniform(
                self.profile["idle_min_sec"], self.profile["idle_max_sec"]
            )

    def update(self, dt, dist_to_target, is_mouse_moving):
        """Updates internal state based on elapsed time dt, target distance, and movement."""
        if self.is_paused or self.is_dragged:
            return self.state

        self.state_timer += dt

        # If in happy petting state
        if self.happy_timer > 0:
            self.happy_timer -= dt
            if self.happy_timer <= 0:
                self.state = PetState.FOCUSED if self.focus_mode else PetState.IDLE
            return self.state

        # If in climbing state, remain climbing until waypoint completed
        if self.state == PetState.CLIMBING:
            return self.state

        # FOCUS MODE: Miu stays calm, sits or watches, does not sleep permanently
        if self.focus_mode:
            if self.state not in (PetState.FOCUSED, PetState.WALKING, PetState.SITTING, PetState.CURIOUS):
                self.state = PetState.FOCUSED
            # Occasional subtle look around
            if self.state == PetState.FOCUSED and self.state_timer > 8.0 and random.random() < 0.04:
                self.state = PetState.CURIOUS
                self.state_timer = 0.0
            elif self.state == PetState.CURIOUS and self.state_timer > 3.0:
                self.state = PetState.FOCUSED
                self.state_timer = 0.0
            return self.state

        # BREAK MODE: Miu stretches, walks gently, or celebrates
        if self.break_mode:
            if self.state not in (PetState.BREAK, PetState.WALKING, PetState.CLIMBING, PetState.STRETCHING):
                self.state = PetState.BREAK
            if self.state_timer > 4.0 and self.state == PetState.BREAK:
                self.state = PetState.STRETCHING
                self.state_timer = 0.0
            return self.state

        # Natural Idle State transitions while waiting for next roam
        if self.state in (PetState.IDLE, PetState.SITTING, PetState.STRETCHING, PetState.SLEEPING):
            # If sleeping, cap nap to personality-calibrated duration
            sleep_cap = self.profile.get("sleep_duration_sec", 9.0)
            if self.state == PetState.SLEEPING and self.state_timer > sleep_cap:
                self.state = PetState.STRETCHING
                self.state_timer = 0.0
            elif self.state == PetState.STRETCHING and self.state_timer > 3.0:
                self.state = PetState.IDLE
                self.state_timer = 0.0

        return self.state
