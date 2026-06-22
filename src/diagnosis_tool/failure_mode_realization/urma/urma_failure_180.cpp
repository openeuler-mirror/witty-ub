#include "urma_failure_180.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure180> g_urma("urma_180");

bool UrmaFailure180::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jetty") != std::string::npos &&
           message.find("failed to fill jetty cfg") != std::string::npos;
}

std::string UrmaFailure180::GetName() const
{
    return "创建Jetty执行失败导致创建Jetty失败";
}

std::string UrmaFailure180::GetRootCauseDesc() const
{
    return "urma_cmd_create_jetty创建Jetty时初始化端口索引或收发WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure180::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure180::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure180::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty，failed to fill jetty cfg。";
}

std::string UrmaFailure180::GetId() const
{
    return "urma_180";
}
} // namespace diag
