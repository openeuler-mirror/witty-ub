#include "hw_break004.h"
#include "../failure_mode_factory.h"

namespace diag {

static AutoRegister<HwBreak004> g_hw("004");

bool HwBreak004::IsValid()
{
    return false;
}

std::string HwBreak004::GetName() const
{
    return "004";
}

std::string HwBreak004::GetRootCauseDesc() const
{
    return "硬件组件发生错误";
}

std::string HwBreak004::GetFixSuggDesc() const
{
    return "联系华为进行硬件更换";
}

std::string HwBreak004::GetValidationMethodDesc() const
{
    return "LocalRAS报错";
}

std::string HwBreak004::GetId() const
{
    return "004";
}
} // namespace diag