#include "urma_failure_678.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure678> g_urma("urma_678");

bool UrmaFailure678::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("set_fd_noblock") != std::string::npos && message.find("ret:") != std::string::npos;
}

std::string UrmaFailure678::GetName() const
{
    return "文件描述符、noblock状态不满足要求导致设置文件描述符、noblock失败";
}

std::string UrmaFailure678::GetRootCauseDesc() const
{
    return "set_fd_noblock执行设置文件描述符、noblock时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure678::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure678::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure678::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：set_fd_noblock，ret:。";
}

std::string UrmaFailure678::GetId() const
{
    return "urma_678";
}
} // namespace diag
