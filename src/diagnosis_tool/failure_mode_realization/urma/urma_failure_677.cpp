#include "urma_failure_677.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure677> g_urma("urma_677");

bool UrmaFailure677::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("set_fd_noblock") != std::string::npos && message.find("flags:") != std::string::npos;
}

std::string UrmaFailure677::GetName() const
{
    return "文件描述符、noblock状态不满足要求导致设置文件描述符、noblock失败";
}

std::string UrmaFailure677::GetRootCauseDesc() const
{
    return "set_fd_noblock执行设置文件描述符、noblock时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure677::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure677::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure677::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：set_fd_noblock，flags:。";
}

std::string UrmaFailure677::GetId() const
{
    return "urma_677";
}
} // namespace diag
