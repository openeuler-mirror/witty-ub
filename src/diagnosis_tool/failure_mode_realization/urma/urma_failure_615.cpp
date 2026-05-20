#include "urma_failure_615.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure615> g_urma("urma_615");

bool UrmaFailure615::IsValid()
{
    return true;
}

std::string UrmaFailure615::GetName() const
{
    return "数据收发失败";
}

std::string UrmaFailure615::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure615::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure615::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure615::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure615::GetId() const
{
    return "urma_615";
}

} // namespace diag
