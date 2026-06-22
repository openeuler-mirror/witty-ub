#include "urma_failure_615.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure615> g_urma("urma_615");

bool UrmaFailure615::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfs_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_get_jfs_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure615::GetName() const
{
    return "获取JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure615::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfs_"
           "opt通过ioctl向驱动提交获取JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure615::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure615::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure615::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfs_opt，ioctl failed in urma_cmd_get_jfs_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure615::GetId() const
{
    return "urma_615";
}
} // namespace diag
