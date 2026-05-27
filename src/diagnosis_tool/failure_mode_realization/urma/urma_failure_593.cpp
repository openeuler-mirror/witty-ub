#include "urma_failure_593.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure593> g_urma("urma_593");

bool UrmaFailure593::IsValid()
{
    return true;
}

std::string UrmaFailure593::GetName() const
{
    return "资源销毁/清理失败";
}

std::string UrmaFailure593::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure593::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure593::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure593::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure593::GetId() const
{
    return "urma_593";
}

} // namespace diag
