#include "urma_failure_262.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure262> g_urma("urma_262");

bool UrmaFailure262::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_token_id") != std::string::npos &&
           message.find("[DRV_ERR]Failed to free token_id, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", tid:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure262::GetName() const
{
    return "释放Token ID、ID执行失败导致释放Token ID、ID失败";
}

std::string UrmaFailure262::GetRootCauseDesc() const
{
    return "urma_free_token_id执行释放Token ID、ID时依赖的释放Token ID、ID步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure262::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure262::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure262::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_token_id，[DRV_ERR]Failed to free token_id, dev_name:，, "
           "eid_idx:，, t"
           "id:，, ret:。";
}

std::string UrmaFailure262::GetId() const
{
    return "urma_262";
}
} // namespace diag
