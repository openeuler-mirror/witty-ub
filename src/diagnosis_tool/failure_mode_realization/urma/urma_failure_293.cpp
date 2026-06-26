#include "urma_failure_293.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure293> g_urma("urma_293");

bool UrmaFailure293::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure293::GetName() const
{
    return "资源导入/注册失败";
}

std::string UrmaFailure293::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure293::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure293::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure293::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure293::GetId() const
{
    return "urma_293";
}
} // namespace diag
