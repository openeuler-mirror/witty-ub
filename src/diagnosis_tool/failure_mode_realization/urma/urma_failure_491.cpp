#include "urma_failure_491.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure491> g_urma("urma_491");

bool UrmaFailure491::IsValid()
{
    return true;
}

std::string UrmaFailure491::GetName() const
{
    return "资源查询失败";
}

std::string UrmaFailure491::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure491::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure491::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure491::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure491::GetId() const
{
    return "urma_491";
}

} // namespace diag
