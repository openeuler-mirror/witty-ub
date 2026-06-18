#include "urma_failure_621.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure621> g_urma("urma_621");

bool UrmaFailure621::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfr_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_set_jfr_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure621::GetName() const
{
    return "设置JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure621::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfr_"
           "opt通过ioctl向驱动提交设置JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure621::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure621::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure621::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfr_opt，ioctl failed in urma_cmd_set_jfr_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure621::GetId() const
{
    return "urma_621";
}
} // namespace diag
