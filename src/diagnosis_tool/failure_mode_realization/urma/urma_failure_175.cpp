#include "urma_failure_175.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure175> g_urma("urma_175");

bool UrmaFailure175::IsValid()
{
    return true;
}

std::string UrmaFailure175::GetName() const
{
    return "资源创建失败";
}

std::string UrmaFailure175::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure175::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure175::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure175::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure175::GetId() const
{
    return "urma_175";
}

} // namespace diag
