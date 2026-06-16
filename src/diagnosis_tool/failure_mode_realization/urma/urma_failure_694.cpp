#include "urma_failure_694.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure694> g_urma("urma_694");

bool UrmaFailure694::IsValid()
{
    return true;
}

std::string UrmaFailure694::GetName() const
{
    return "设备/驱动交互失败";
}

std::string UrmaFailure694::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure694::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure694::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure694::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure694::GetId() const
{
    return "urma_694";
}

} // namespace diag
