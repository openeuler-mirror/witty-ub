#include "urma_failure_717.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure717> g_urma("urma_717");

bool UrmaFailure717::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfs") != std::string::npos &&
           message.find("Failed to exec ops->active_jfs.") != std::string::npos;
}

std::string UrmaFailure717::GetName() const
{
    return "激活JFS执行失败导致激活JFS失败";
}

std::string UrmaFailure717::GetRootCauseDesc() const
{
    return "urma_active_jfs执行激活JFS时依赖的激活JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure717::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure717::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure717::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，Failed to exec ops->active_jfs.。";
}

std::string UrmaFailure717::GetId() const
{
    return "urma_717";
}
} // namespace diag
