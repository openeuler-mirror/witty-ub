#include "urma_failure_712.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure712> g_urma("urma_712");

bool UrmaFailure712::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfs_opt") != std::string::npos &&
           message.find("Failed to exec ops->set_jfs_opt.") != std::string::npos;
}

std::string UrmaFailure712::GetName() const
{
    return "设置JFS执行失败导致设置JFS失败";
}

std::string UrmaFailure712::GetRootCauseDesc() const
{
    return "urma_set_jfs_opt执行设置JFS时依赖的设置JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure712::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure712::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure712::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，Failed to exec ops->set_jfs_opt.。";
}

std::string UrmaFailure712::GetId() const
{
    return "urma_712";
}
} // namespace diag
