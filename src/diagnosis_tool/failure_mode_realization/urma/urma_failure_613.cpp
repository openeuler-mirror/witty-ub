#include "urma_failure_613.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure613> g_urma("urma_613");

bool UrmaFailure613::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfs_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_set_jfs_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure613::GetName() const
{
    return "设置JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure613::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfs_"
           "opt通过ioctl向驱动提交设置JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure613::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure613::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure613::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfs_opt，ioctl failed in urma_cmd_set_jfs_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure613::GetId() const
{
    return "urma_613";
}
} // namespace diag
