#include "urma_failure_718.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure718> g_urma("urma_718");

bool UrmaFailure718::IsValid()
{
    return true;
}

std::string UrmaFailure718::GetName() const
{
    return "其他URMA故障";
}

std::string UrmaFailure718::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure718::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure718::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure718::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure718::GetId() const
{
    return "urma_718";
}

} // namespace diag
