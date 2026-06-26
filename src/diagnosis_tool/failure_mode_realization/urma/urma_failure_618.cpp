#include "urma_failure_618.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure618> g_urma("urma_618");

bool UrmaFailure618::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jfr") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_modify_jfr, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure618::GetName() const
{
    return "修改JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure618::GetRootCauseDesc() const
{
    return "urma_cmd_modify_"
           "jfr通过ioctl向驱动提交修改JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure618::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure618::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure618::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfr，ioctl failed in urma_cmd_modify_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure618::GetId() const
{
    return "urma_618";
}
} // namespace diag
