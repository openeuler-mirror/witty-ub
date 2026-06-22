#include "urma_failure_011.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure011> g_urma("urma_011");

bool UrmaFailure011::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to init jetty send wr buf") != std::string::npos;
}

std::string UrmaFailure011::GetName() const
{
    return "创建Jetty执行失败导致创建Jetty失败";
}

std::string UrmaFailure011::GetRootCauseDesc() const
{
    return "bondp_create_jetty创建Jetty时初始化端口索引或收发WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure011::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure011::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure011::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to init jetty send wr buf。";
}

std::string UrmaFailure011::GetId() const
{
    return "urma_011";
}
} // namespace diag
