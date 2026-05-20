#include "urma_failure_692.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure692> g_urma("urma_692");

bool UrmaFailure692::IsValid()
{
    return true;
}

std::string UrmaFailure692::GetName() const
{
    return "资源销毁/清理失败";
}

std::string UrmaFailure692::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure692::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure692::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure692::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure692::GetId() const
{
    return "urma_692";
}

} // namespace diag
