#include "urma_failure_008.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure008> g_urma("urma_008");

bool UrmaFailure008::IsValid()
{
    return true;
}

std::string UrmaFailure008::GetName() const
{
    return "建链失败";
}

std::string UrmaFailure008::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure008::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure008::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure008::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure008::GetId() const
{
    return "urma_008";
}

} // namespace diag
