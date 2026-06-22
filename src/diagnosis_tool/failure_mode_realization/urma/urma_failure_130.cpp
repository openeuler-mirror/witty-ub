#include "urma_failure_130.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure130> g_urma("urma_130");

bool UrmaFailure130::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure130::GetName() const
{
    return "资源创建失败";
}

std::string UrmaFailure130::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure130::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure130::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure130::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure130::GetId() const
{
    return "urma_130";
}
} // namespace diag
