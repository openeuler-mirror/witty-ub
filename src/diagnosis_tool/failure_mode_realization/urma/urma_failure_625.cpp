#include "urma_failure_625.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure625> g_urma("urma_625");

bool UrmaFailure625::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jfr") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_active_jfr, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure625::GetName() const
{
    return "激活JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure625::GetRootCauseDesc() const
{
    return "urma_cmd_active_"
           "jfr通过ioctl向驱动提交激活JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure625::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure625::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure625::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfr，ioctl failed in urma_cmd_active_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure625::GetId() const
{
    return "urma_625";
}
} // namespace diag
