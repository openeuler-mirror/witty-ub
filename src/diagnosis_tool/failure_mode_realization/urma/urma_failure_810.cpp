#include "urma_failure_810.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure810> g_urma("urma_810");

bool UrmaFailure810::IsValid()
{
    return true;
}

std::string UrmaFailure810::GetName() const
{
    return "设备/驱动交互失败";
}

std::string UrmaFailure810::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure810::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure810::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure810::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure810::GetId() const
{
    return "urma_810";
}

} // namespace diag
