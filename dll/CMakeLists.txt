# Japanese to Phoneme Converter - FFI/DLL Edition
# Cross-platform CMake build configuration
# Supports Windows (DLL), Linux (SO), macOS (DYLIB)

cmake_minimum_required(VERSION 3.15)
project(jpn_to_phoneme_ffi VERSION 1.0.0 LANGUAGES CXX)

# Set C++ standard to C++17 for optimal performance and modern features
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build type defaults to Release for maximum performance
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
endif()

# ============================================================================
# Compiler flags for blazing fast performance
# ============================================================================

if(MSVC)
    # Microsoft Visual C++ - Maximum optimization
    add_compile_options(
        /O2          # Maximum optimization (speed)
        /Ob2         # Inline function expansion
        /Oi          # Enable intrinsic functions
        /Ot          # Favor fast code
        /GL          # Whole program optimization
        /GF          # String pooling
        /Gy          # Function-level linking
        /W4          # Warning level 4
        /utf-8       # UTF-8 source and execution charset
    )
    # Link-time code generation for release builds
    if(CMAKE_BUILD_TYPE MATCHES Release)
        add_link_options(/LTCG)
    endif()
else()
    # GCC/Clang - Aggressive optimization flags
    add_compile_options(
        -O3                    # Maximum optimization
        -march=native          # Optimize for host CPU architecture
        -ffast-math           # Fast floating point math
        -funroll-loops        # Loop unrolling
        -fomit-frame-pointer  # Omit frame pointer for extra register
        -Wall                 # All warnings
        -Wextra              # Extra warnings
    )
    
    # Platform-specific optimizations
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        add_compile_options(-pthread)
        add_link_options(-pthread)
    endif()
endif()

# ============================================================================
# Build shared library (DLL/SO/DYLIB)
# ============================================================================

add_library(jpn_to_phoneme_ffi SHARED jpn_to_phoneme_ffi.cpp)

# Set library properties for cross-platform compatibility
set_target_properties(jpn_to_phoneme_ffi PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    
    # Output naming conventions
    PREFIX ""  # Remove 'lib' prefix on Unix systems for consistency
    
    # Position-independent code for shared libraries
    POSITION_INDEPENDENT_CODE ON
    
    # C++ visibility for proper symbol export (Unix only)
    CXX_VISIBILITY_PRESET default
)

# Platform-specific output names
if(WIN32)
    set_target_properties(jpn_to_phoneme_ffi PROPERTIES OUTPUT_NAME "jpn_to_phoneme_ffi")
elseif(APPLE)
    set_target_properties(jpn_to_phoneme_ffi PROPERTIES OUTPUT_NAME "jpn_to_phoneme_ffi")
else()
    set_target_properties(jpn_to_phoneme_ffi PROPERTIES OUTPUT_NAME "jpn_to_phoneme_ffi")
endif()

# ============================================================================
# Installation rules
# ============================================================================

# Install library to lib directory
install(TARGETS jpn_to_phoneme_ffi
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

# ============================================================================
# Build information output
# ============================================================================

message(STATUS "")
message(STATUS "╔════════════════════════════════════════════════════════╗")
message(STATUS "║  Japanese to Phoneme Converter - FFI/DLL Build        ║")
message(STATUS "╚════════════════════════════════════════════════════════╝")
message(STATUS "")
message(STATUS "Build Configuration:")
message(STATUS "  • Platform:        ${CMAKE_SYSTEM_NAME}")
message(STATUS "  • Compiler:        ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "  • Build Type:      ${CMAKE_BUILD_TYPE}")
message(STATUS "  • C++ Standard:    C++${CMAKE_CXX_STANDARD}")
message(STATUS "  • Architecture:    ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "")
message(STATUS "Output Library:")
if(WIN32)
    message(STATUS "  • Type:            DLL (Windows)")
    message(STATUS "  • Extension:       .dll")
elseif(APPLE)
    message(STATUS "  • Type:            DYLIB (macOS)")
    message(STATUS "  • Extension:       .dylib")
else()
    message(STATUS "  • Type:            SO (Linux)")
    message(STATUS "  • Extension:       .so")
endif()
message(STATUS "")

