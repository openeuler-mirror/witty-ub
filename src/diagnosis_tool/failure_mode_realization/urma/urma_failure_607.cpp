#include "urma_failure_607.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure607> g_urma("urma_607");

bool UrmaFailure607::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure607::GetName() const
{
    return "设备/驱动交互失败";
}

std::string UrmaFailure607::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure607::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure607::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure607::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure607::GetId() const
{
    return "urma_607";
}
} // namespace diag
