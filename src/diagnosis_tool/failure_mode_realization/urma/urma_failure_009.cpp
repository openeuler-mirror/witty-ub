#include "urma_failure_009.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure009> g_urma("urma_009");

bool UrmaFailure009::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfr") != std::string::npos &&
           message.find("Failed to init jfr wr buf") != std::string::npos;
}

std::string UrmaFailure009::GetName() const
{
    return "创建JFR执行失败导致创建JFR失败";
}

std::string UrmaFailure009::GetRootCauseDesc() const
{
    return "bondp_create_jfr创建JFR时初始化端口索引或WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure009::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure009::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure009::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfr，Failed to init jfr wr buf。";
}

std::string UrmaFailure009::GetId() const
{
    return "urma_009";
}
} // namespace diag
