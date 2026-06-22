#include "urma_failure_616.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure616> g_urma("urma_616");

bool UrmaFailure616::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfs_opt") != std::string::npos &&
           message.find("Invalid out buffer from kernel.") != std::string::npos;
}

std::string UrmaFailure616::GetName() const
{
    return "JFS状态不满足要求导致获取JFS失败";
}

std::string UrmaFailure616::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfs_opt执行获取JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure616::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure616::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure616::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfs_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure616::GetId() const
{
    return "urma_616";
}
} // namespace diag
