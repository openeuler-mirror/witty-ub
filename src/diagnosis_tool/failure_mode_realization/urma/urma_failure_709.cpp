#include "urma_failure_709.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure709> g_urma("urma_709");

bool UrmaFailure709::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfs_opt") != std::string::npos &&
           message.find("Failed to set opt, jfs has been activated") != std::string::npos;
}

std::string UrmaFailure709::GetName() const
{
    return "设置JFS执行失败导致设置JFS失败";
}

std::string UrmaFailure709::GetRootCauseDesc() const
{
    return "urma_set_jfs_opt执行设置JFS时依赖的设置JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure709::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure709::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure709::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，Failed to set opt, jfs has been activated。";
}

std::string UrmaFailure709::GetId() const
{
    return "urma_709";
}
} // namespace diag
