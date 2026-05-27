#include "urma_failure_052.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure052> g_urma("urma_052");

bool UrmaFailure052::IsValid()
{
    return true;
}

std::string UrmaFailure052::GetName() const
{
    return "建链失败";
}

std::string UrmaFailure052::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure052::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure052::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure052::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure052::GetId() const
{
    return "urma_052";
}

} // namespace diag
