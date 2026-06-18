#include "urma_failure_218.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure218> g_urma("urma_218");

bool UrmaFailure218::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure218::GetName() const
{
    return "资源查询失败";
}

std::string UrmaFailure218::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure218::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure218::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure218::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure218::GetId() const
{
    return "urma_218";
}
} // namespace diag
