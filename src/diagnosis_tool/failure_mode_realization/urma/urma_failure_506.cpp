#include "urma_failure_506.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure506> g_urma("urma_506");

bool UrmaFailure506::IsValid()
{
    return true;
}

std::string UrmaFailure506::GetName() const
{
    return "资源导入/注册失败";
}

std::string UrmaFailure506::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure506::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure506::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure506::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure506::GetId() const
{
    return "urma_506";
}

} // namespace diag
