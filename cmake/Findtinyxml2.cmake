# Fallback Find module for tinyxml2 on systems without a CMake config
include(FindPackageHandleStandardArgs)
find_path(tinyxml2_INCLUDE_DIR NAMES tinyxml2.h)
find_library(tinyxml2_LIBRARY NAMES tinyxml2)
find_package_handle_standard_args(tinyxml2 DEFAULT_MSG tinyxml2_LIBRARY tinyxml2_INCLUDE_DIR)
if(tinyxml2_FOUND AND NOT TARGET tinyxml2::tinyxml2)
    add_library(tinyxml2::tinyxml2 UNKNOWN IMPORTED)
    set_target_properties(tinyxml2::tinyxml2 PROPERTIES
        IMPORTED_LOCATION "${tinyxml2_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${tinyxml2_INCLUDE_DIR}")
endif()
