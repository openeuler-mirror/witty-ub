#include "urma_failure_001.h"
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<UrmaFailure001> g_urma("urma_001");

bool UrmaFailure001::IsValid()
{
    return true;
}

std::string UrmaFailure001::GetName() const
{
    return "初始化失败";
}

std::string UrmaFailure001::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause UrmaFailure001::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure001::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure001::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string UrmaFailure001::GetId() const
{
    return "urma_001";
}

} // namespace diag
