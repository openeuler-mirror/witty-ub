#include "hw_break005.h"
#include "../failure_mode_factory.h"

namespace diag {

static AutoRegister<HwBreak005> g_hw("005");

bool HwBreak005::IsValid()
{
    return true;
}

std::string HwBreak005::GetName() const
{
    return "005";
}

std::string HwBreak005::GetRootCauseDesc() const
{
    return "硬件组件发生错误";
}

std::string HwBreak005::GetFixSuggDesc() const
{
    return "联系华为进行硬件更换";
}

std::string HwBreak005::GetValidationMethodDesc() const
{
    return "LocalRAS报错";
}

std::string HwBreak005::GetId() const
{
    return "005";
}
} // namespace diag