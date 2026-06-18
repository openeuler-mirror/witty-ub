#include "urma_failure_352.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure352> g_urma("urma_352");

bool UrmaFailure352::IsValid(const std::vector<std::string> &fields)
{
    return true;
}

std::string UrmaFailure352::GetName() const
{
    return "数据收发失败";
}

std::string UrmaFailure352::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure352::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure352::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure352::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure352::GetId() const
{
    return "urma_352";
}
} // namespace diag
