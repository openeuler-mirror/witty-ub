#include "hw003_break.h"
#include "../failure_mode_factory.h"

namespace diag {

static AutoRegister<HwBreak003> hw("003");

bool HwBreak003::isValid() {
    return true;
}

std::string HwBreak003::GetName () const{
    return "003";
}

std::string HwBreak003::GetRootCauseDesc () const{
    return "硬件组件发生错误";
}

std::string HwBreak003::GetFixSuggDesc () const{
    return "联系华为进行硬件更换";
}

std::string HwBreak003::GetValidationMethodDesc () const{
    return "LocalRAS报错";
}

std::string HwBreak003::GetId () const{
    return "003";
}
}