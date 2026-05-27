#include "urma_failure_546.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure546> g_urma("urma_546");

bool UrmaFailure546::IsValid()
{
    return true;
}

std::string UrmaFailure546::GetName() const
{
    return "数据收发失败";
}

std::string UrmaFailure546::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure546::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure546::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure546::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure546::GetId() const
{
    return "urma_546";
}

} // namespace diag
