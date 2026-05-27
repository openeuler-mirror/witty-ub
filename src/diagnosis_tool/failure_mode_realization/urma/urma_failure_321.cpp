#include "urma_failure_321.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure321> g_urma("urma_321");

bool UrmaFailure321::IsValid()
{
    return true;
}

std::string UrmaFailure321::GetName() const
{
    return "资源创建失败";
}

std::string UrmaFailure321::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure321::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure321::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure321::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure321::GetId() const
{
    return "urma_321";
}

} // namespace diag
