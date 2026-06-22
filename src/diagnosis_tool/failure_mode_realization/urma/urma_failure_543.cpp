#include "urma_failure_543.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure543> g_urma("urma_543");

bool UrmaFailure543::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfr") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_delete_jfr , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure543::GetName() const
{
    return "释放JFR ioctl驱动命令返回失败";
}

std::string UrmaFailure543::GetRootCauseDesc() const
{
    return "urma_cmd_free_"
           "jfr通过ioctl向驱动提交释放JFR命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure543::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure543::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure543::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfr，ioctl failed in urma_cmd_delete_jfr , ret:，, "
           "errno:。";
}

std::string UrmaFailure543::GetId() const
{
    return "urma_543";
}
} // namespace diag
