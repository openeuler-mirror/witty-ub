#include "urma_failure_346.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure346> g_urma("urma_346");

bool UrmaFailure346::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_token_id") != std::string::npos && message.find("ref:") != std::string::npos &&
           message.find(", not zero") != std::string::npos;
}

std::string UrmaFailure346::GetName() const
{
    return "Token ID、ID状态不满足要求导致释放Token ID、ID失败";
}

std::string UrmaFailure346::GetRootCauseDesc() const
{
    return "urma_free_token_id执行释放Token ID、ID时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure346::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure346::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure346::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_token_id，ref:，, not zero。";
}

std::string UrmaFailure346::GetId() const
{
    return "urma_346";
}
} // namespace diag
