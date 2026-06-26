#include "urma_failure_174.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure174> g_urma("urma_174");

bool UrmaFailure174::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfr") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_create_jfr, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure174::GetName() const
{
    return "创建JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure174::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "jfr通过ioctl向驱动提交创建JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure174::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure174::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure174::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfr，ioctl failed in urma_cmd_create_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure174::GetId() const
{
    return "urma_174";
}
} // namespace diag
