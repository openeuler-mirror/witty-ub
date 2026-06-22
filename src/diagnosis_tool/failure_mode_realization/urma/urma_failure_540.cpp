#include "urma_failure_540.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure540> g_urma("urma_540");

bool UrmaFailure540::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_delete_jfr_batch , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure540::GetName() const
{
    return "删除JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure540::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_"
           "batch通过ioctl向驱动提交删除JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure540::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure540::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure540::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，ioctl failed in urma_cmd_delete_jfr_batch , "
           "ret:，, "
           "errno:。";
}

std::string UrmaFailure540::GetId() const
{
    return "urma_540";
}
} // namespace diag
