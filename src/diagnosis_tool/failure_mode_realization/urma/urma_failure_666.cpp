#include "urma_failure_666.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure666> g_urma("urma_666");

bool UrmaFailure666::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure666::GetName() const
{
    return "其他URMA故障";
}

std::string UrmaFailure666::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure666::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure666::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure666::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure666::GetId() const
{
    return "urma_666";
}
} // namespace diag
