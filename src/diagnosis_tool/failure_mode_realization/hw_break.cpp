#include "hw_break.h"
#include "../failure_mode_factory.h"

namespace diag {

static AutoRegister<HwBreak> g_hw("002");

bool HwBreak::IsValid(std::string &logContent)
{
    logContent.clear();
    return true;
}

std::string HwBreak::GetName() const
{
    return "002";
}

std::string HwBreak::GetRootCauseDesc() const
{
    return "硬件组件发生错误";
}

std::string HwBreak::GetFixSuggDesc() const
{
    return "联系华为进行硬件更换";
}

std::string HwBreak::GetValidationMethodDesc() const
{
    return "LocalRAS报错";
}

std::string HwBreak::GetId() const
{
    return "002";
}
} // namespace diag
