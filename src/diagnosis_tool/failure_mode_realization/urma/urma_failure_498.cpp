#include "urma_failure_498.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure498> g_urma("urma_498");

bool UrmaFailure498::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure498::GetName() const
{
    return "资源销毁/清理失败";
}

std::string UrmaFailure498::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure498::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure498::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure498::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure498::GetId() const
{
    return "urma_498";
}
} // namespace diag
