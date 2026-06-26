#include "urma_failure_617.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure617> g_urma("urma_617");

bool UrmaFailure617::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jfs") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_active_jfs, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure617::GetName() const
{
    return "激活JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure617::GetRootCauseDesc() const
{
    return "urma_cmd_active_"
           "jfs通过ioctl向驱动提交激活JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure617::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure617::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure617::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfs，ioctl failed in urma_cmd_active_jfs, ret:，, "
           "errno:。";
}

std::string UrmaFailure617::GetId() const
{
    return "urma_617";
}
} // namespace diag
