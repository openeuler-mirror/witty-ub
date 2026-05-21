#include "urma_failure_833.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure833> g_urma("urma_833");

bool UrmaFailure833::IsValid()
{
    return true;
}

std::string UrmaFailure833::GetName() const
{
    return "其他URMA故障";
}

std::string UrmaFailure833::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure833::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure833::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure833::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure833::GetId() const
{
    return "urma_833";
}

} // namespace diag
