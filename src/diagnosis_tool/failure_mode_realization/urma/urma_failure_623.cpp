#include "urma_failure_623.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure623> g_urma("urma_623");

bool UrmaFailure623::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfr_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_get_jfr_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure623::GetName() const
{
    return "获取JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure623::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfr_"
           "opt通过ioctl向驱动提交获取JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure623::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure623::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure623::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，ioctl failed in urma_cmd_get_jfr_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure623::GetId() const
{
    return "urma_623";
}
} // namespace diag
