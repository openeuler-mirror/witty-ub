#include "urma_failure_008.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure008> g_urma("urma_008");

bool UrmaFailure008::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfr") != std::string::npos &&
           message.find("Failed to init active indices") != std::string::npos;
}

std::string UrmaFailure008::GetName() const
{
    return "创建JFR执行失败导致创建JFR失败";
}

std::string UrmaFailure008::GetRootCauseDesc() const
{
    return "bondp_create_jfr创建JFR时初始化端口索引或WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure008::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure008::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure008::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfr，Failed to init active indices。";
}

std::string UrmaFailure008::GetId() const
{
    return "urma_008";
}
} // namespace diag
