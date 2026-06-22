#include "urma_failure_051.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure051> g_urma("urma_051");

bool UrmaFailure051::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure051::GetName() const
{
    return "建链失败";
}

std::string UrmaFailure051::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure051::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure051::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure051::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure051::GetId() const
{
    return "urma_051";
}
} // namespace diag
