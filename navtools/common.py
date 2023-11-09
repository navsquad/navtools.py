import numpy as np
from numba import njit
from numpy.typing import ArrayLike

from navtools.conversions import ecef2lla, ecef2enu


# Line-of-Sight States
@njit(cache=True)
def compute_visibility_status(
    rx_pos: np.array, emitter_pos: np.array, mask_angle: float = 10.0
) -> tuple[bool, float, float]:
    """computes visibility of emitter from receiver location in ECEF reference frame

    Parameters
    ----------
    rx_pos : np.array
        receiver position(s) in ECEF reference frame
    emitter_pos : np.array
        emitter position(s) in ECEF reference frame
    mask_angle : float, optional
        mask angle experienced at receiver position(s), by default 10.0

    Returns
    -------
    tuple[bool, float, float]
        emitter visibility status, emitter azimuth (rad), emitter elevation(rad)
    """
    emitter_az, emitter_el = compute_az_and_el(rx_pos=rx_pos, emitter_pos=emitter_pos)
    is_visible = np.degrees(emitter_el) >= mask_angle

    return is_visible, emitter_az, emitter_el


@njit(cache=True)
def compute_az_and_el(rx_pos: np.array, emitter_pos: np.array) -> tuple[float, float]:
    """computes azimuth and elevation of emitter from receiver location in ECEF reference frame

    Parameters
    ----------
    rx_pos : np.array
        receiver position(s) in ECEF reference frame
    emitter_pos : np.array
        emitter position(s) in ECEF reference frame

    Returns
    -------
    tuple[float, float]
        emitter azimuth (rad), emitter elevation (rad)
    """
    range, _ = compute_range_and_unit_vector(rx_pos=rx_pos, emitter_pos=emitter_pos)
    lla = ecef2lla(x=rx_pos[0], y=rx_pos[1], z=rx_pos[2])
    enu = ecef2enu(
        x=emitter_pos[0],
        y=emitter_pos[1],
        z=emitter_pos[2],
        lat0=lla.lat,
        lon0=lla.lon,
        alt0=lla.alt,
    )
    el = np.arcsin(enu.up / range)
    az = np.arctan2(enu.east, enu.north)

    return az, el


@njit(cache=True)
def compute_range_and_unit_vector(
    rx_pos: np.array, emitter_pos: np.array
) -> tuple[float, np.array]:
    """computes range and unit vector to emitter from receiver location in ECEF reference frame

    Parameters
    ----------
    rx_pos : np.array
        receiver position(s) in ECEF reference frame
    emitter_pos : np.array
        emitter position(s) in ECEF reference frame

    Returns
    -------
    tuple[float, np.array]
        range (m), unit vector in ECEF reference frame
    """
    rx_pos_rel_sat = rx_pos - emitter_pos
    range = np.sqrt(np.sum(rx_pos_rel_sat**2))
    unit_vector = rx_pos_rel_sat / range

    return range, unit_vector


@njit(cache=True)
def compute_range_rate(
    rx_vel: np.array, emitter_vel: np.array, unit_vector: np.array
) -> float:
    """computes range rate from receiver and emitter velocities in ECEF reference frame

    Parameters
    ----------
    rx_vel : np.array
        receiver velocity(s) in ECEF reference frame
    emitter_vel : np.array
        emitter velocity(s) in ECEF reference frame
    unit_vector : np.array
        unit vector in ECEF reference frame

    Returns
    -------
    float
        range rate (m/s)
    """
    rx_vel_rel_sat = rx_vel - emitter_vel
    range_rate = np.sum(rx_vel_rel_sat * unit_vector)

    return range_rate


# Bitwise Operations
@njit(cache=True)
def get_bit_value(number: int, index: int):
    return (number >> index) & 1


@njit(cache=True)
def set_bit_value(number: int, index: int):
    return number | (1 << index)


@njit(cache=True)
def xor_register_taps(register: int, nbits: int, taps: ArrayLike):
    xor = 0
    for tap in taps:
        xor ^= register >> (nbits - tap)

    return xor & 1


@njit(cache=True)
def msequence(nbits: int, taps: ArrayLike, state: int = None):
    length = 2**nbits - 1

    if state is None:
        lfsr = length
    else:
        lfsr = state

    sequence = []
    for _ in range(length):
        sequence.append(get_bit_value(number=lfsr, index=0))
        feedback = xor_register_taps(register=lfsr, nbits=nbits, taps=taps)
        lfsr = (lfsr >> 1) | (feedback << int((nbits - 1)))

    sequence = np.array(sequence)

    return sequence


@njit(cache=True)
def nextpow2(integer: int):
    return 1 << (integer - 1).bit_length()
