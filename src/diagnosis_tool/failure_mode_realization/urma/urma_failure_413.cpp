#include "urma_failure_413.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure413> g_urma("urma_413");

bool UrmaFailure413::IsValid()
{
    return true;
}

std::string UrmaFailure413::GetName() const
{
    return "资源查询失败";
}

std::string UrmaFailure413::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure413::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure413::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure413::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure413::GetId() const
{
    return "urma_413";
}

} // namespace diag
