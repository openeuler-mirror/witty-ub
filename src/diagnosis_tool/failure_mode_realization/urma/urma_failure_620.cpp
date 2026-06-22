#include "urma_failure_620.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure620> g_urma("urma_620");

bool UrmaFailure620::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_jfr") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure620::GetName() const
{
    return "查询JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure620::GetRootCauseDesc() const
{
    return "urma_cmd_query_"
           "jfr通过ioctl向驱动提交查询JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure620::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure620::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure620::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jfr，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure620::GetId() const
{
    return "urma_620";
}
} // namespace diag
