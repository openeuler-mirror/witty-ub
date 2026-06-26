#include "urma_failure_010.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure010> g_urma("urma_010");

bool UrmaFailure010::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to init active indices") != std::string::npos;
}

std::string UrmaFailure010::GetName() const
{
    return "创建Jetty执行失败导致创建Jetty失败";
}

std::string UrmaFailure010::GetRootCauseDesc() const
{
    return "bondp_create_jetty创建Jetty时初始化端口索引或收发WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure010::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure010::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure010::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to init active indices。";
}

std::string UrmaFailure010::GetId() const
{
    return "urma_010";
}
} // namespace diag
