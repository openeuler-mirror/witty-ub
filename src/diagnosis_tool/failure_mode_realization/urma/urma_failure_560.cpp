#include "urma_failure_560.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure560> g_urma("urma_560");

bool UrmaFailure560::IsValid()
{
    return true;
}

std::string UrmaFailure560::GetName() const
{
    return "资源导入/注册失败";
}

std::string UrmaFailure560::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure560::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure560::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure560::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure560::GetId() const
{
    return "urma_560";
}

} // namespace diag
